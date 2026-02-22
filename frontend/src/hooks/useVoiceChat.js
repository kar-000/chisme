/**
 * useVoiceChat — WebRTC P2P voice chat hook.
 *
 * Mic access is optional. If getUserMedia fails the user still joins voice
 * (listen-only) so their chip appears and they can hear others.
 *
 * Protocol:
 *   - On join: send voice.join over WS, get voice.user_joined broadcast (including self)
 *   - Other peers send voice.offer → we respond with voice.answer
 *   - We send voice.offer to peers who were already in the channel
 *   - ICE candidates exchanged via voice.ice_candidate (targeted)
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import useChatStore from '../store/chatStore'

const ICE_SERVERS = [{ urls: 'stun:stun.l.google.com:19302' }]

export function useVoiceChat(channelId, currentUser, sendMsg) {
  const [inVoice, setInVoice] = useState(false)
  const [muted, setMuted] = useState(true)
  const [micError, setMicError] = useState(null)

  const localStreamRef = useRef(null)
  // peerId → RTCPeerConnection
  const peersRef = useRef({})
  const inVoiceRef = useRef(false)
  // Refs for speaking detection (avoid stale closures in setInterval)
  const mutedRef = useRef(true)
  const speakingIntervalRef = useRef(null)
  const audioContextRef = useRef(null)

  const voiceUsers = useChatStore((s) => s.voiceUsers)
  const pendingVoiceSignals = useChatStore((s) => s.pendingVoiceSignals)
  const consumeVoiceSignals = useChatStore((s) => s.consumeVoiceSignals)

  // ── Helper: create a peer connection to a remote user ──────────────────────
  const createPeer = useCallback((remoteUserId, isInitiator) => {
    if (!currentUser) return null
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS })

    // Add local tracks (may be empty if no mic)
    localStreamRef.current?.getTracks().forEach((t) => pc.addTrack(t, localStreamRef.current))

    // ICE candidate → send to peer via WS
    pc.onicecandidate = (ev) => {
      if (ev.candidate) {
        sendMsg({
          type: 'voice.ice_candidate',
          target_user_id: remoteUserId,
          candidate: ev.candidate,
        })
      }
    }

    // Remote track → play audio (guard against duplicate elements on renegotiation)
    pc.ontrack = (ev) => {
      const existing = document.querySelector(`audio[data-peer-id="${remoteUserId}"]`)
      if (existing) {
        existing.srcObject = ev.streams[0]
        existing.play().catch((err) => console.warn('useVoiceChat: audio resume blocked', err))
        return
      }
      const audio = document.createElement('audio')
      audio.srcObject = ev.streams[0]
      audio.autoplay = true
      audio.setAttribute('data-peer-id', String(remoteUserId))
      document.body.appendChild(audio)
      // autoplay attribute alone is not reliable for MediaStream sources —
      // explicit play() is required by most browsers.
      audio.play().catch((err) => console.warn('useVoiceChat: audio play blocked', err))
    }

    pc.onconnectionstatechange = () => {
      if (['disconnected', 'failed', 'closed'].includes(pc.connectionState)) {
        closePeer(remoteUserId)
      }
    }

    if (isInitiator) {
      pc.onnegotiationneeded = async () => {
        try {
          const offer = await pc.createOffer()
          await pc.setLocalDescription(offer)
          sendMsg({
            type: 'voice.offer',
            target_user_id: remoteUserId,
            sdp: pc.localDescription,
          })
        } catch (err) {
          console.error('useVoiceChat: offer error', err)
        }
      }
    }

    peersRef.current[remoteUserId] = pc
    return pc
  }, [currentUser, sendMsg])

  // ── Helper: close a peer connection ───────────────────────────────────────
  const closePeer = useCallback((remoteUserId) => {
    const pc = peersRef.current[remoteUserId]
    if (pc) {
      pc.close()
      delete peersRef.current[remoteUserId]
    }
    document.querySelector(`audio[data-peer-id="${remoteUserId}"]`)?.remove()
  }, [])

  // ── Handle incoming WS voice signals ──────────────────────────────────────
  useEffect(() => {
    if (!inVoice || pendingVoiceSignals.length === 0) return
    const signals = consumeVoiceSignals()
    ;(async () => {
      for (const sig of signals) {
        if (!inVoiceRef.current) break
        const { type, from_user_id, sdp, candidate } = sig

        if (type === 'voice.offer') {
          let pc = peersRef.current[from_user_id]
          if (!pc) pc = createPeer(from_user_id, false)
          try {
            await pc.setRemoteDescription(new RTCSessionDescription(sdp))
            const answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            sendMsg({
              type: 'voice.answer',
              target_user_id: from_user_id,
              sdp: pc.localDescription,
            })
          } catch (err) {
            console.error('useVoiceChat: answer error', err)
          }
        } else if (type === 'voice.answer') {
          const pc = peersRef.current[from_user_id]
          if (pc && pc.signalingState !== 'stable') {
            try {
              await pc.setRemoteDescription(new RTCSessionDescription(sdp))
            } catch (err) {
              console.error('useVoiceChat: setRemoteDescription error', err)
            }
          }
        } else if (type === 'voice.ice_candidate') {
          const pc = peersRef.current[from_user_id]
          if (pc) {
            try {
              await pc.addIceCandidate(new RTCIceCandidate(candidate))
            } catch (err) {
              console.error('useVoiceChat: addIceCandidate error', err)
            }
          }
        }
      }
    })()
  }, [pendingVoiceSignals, inVoice, consumeVoiceSignals, createPeer, sendMsg])

  // ── When a new voice user joins (while we're in voice), initiate offer ─────
  // Tiebreaker: lower user ID always initiates to prevent offer collisions
  // when both peers join simultaneously and both try to create offers.
  useEffect(() => {
    if (!inVoice || !currentUser) return
    Object.keys(voiceUsers).forEach((uid) => {
      const userId = Number(uid)
      if (userId === currentUser.id) return       // skip self
      if (!peersRef.current[userId]) {
        createPeer(userId, currentUser.id < userId)
      }
    })
  }, [voiceUsers, inVoice, currentUser, createPeer])

  // ── Speaking detection via Web Audio API ──────────────────────────────────
  const startSpeakingDetection = useCallback((stream) => {
    try {
      const ctx = new AudioContext()
      audioContextRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 512
      source.connect(analyser)
      const buffer = new Uint8Array(analyser.frequencyBinCount)

      let lastSpeaking = false
      speakingIntervalRef.current = setInterval(() => {
        if (!inVoiceRef.current) return
        analyser.getByteFrequencyData(buffer)
        // RMS of the frequency data as a volume proxy
        const rms = Math.sqrt(buffer.reduce((sum, v) => sum + v * v, 0) / buffer.length)
        const speaking = !mutedRef.current && rms > 15
        if (speaking !== lastSpeaking) {
          lastSpeaking = speaking
          sendMsg({ type: 'voice.state_update', muted: mutedRef.current, video: false, speaking })
        }
      }, 200)
    } catch {
      // AudioContext not supported — skip speaking detection
    }
  }, [sendMsg])

  const stopSpeakingDetection = useCallback(() => {
    clearInterval(speakingIntervalRef.current)
    speakingIntervalRef.current = null
    audioContextRef.current?.close().catch(() => {})
    audioContextRef.current = null
  }, [])

  // ── Join voice ─────────────────────────────────────────────────────────────
  const joinVoice = useCallback(async () => {
    if (inVoiceRef.current) return
    setMicError(null)

    // Try to get microphone — continue even if it fails (listen-only)
    try {
      if (navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        localStreamRef.current = stream
        mutedRef.current = false
        setMuted(false)
        startSpeakingDetection(stream)
      } else {
        setMicError('no-api')
      }
    } catch (err) {
      console.warn('useVoiceChat: mic unavailable, joining listen-only:', err.name)
      setMicError(err.name)
      // localStreamRef.current stays null — listen-only mode
    }

    inVoiceRef.current = true
    setInVoice(true)
    sendMsg({ type: 'voice.join', muted: localStreamRef.current === null, video: false })
  }, [sendMsg, startSpeakingDetection])

  // ── Leave voice ────────────────────────────────────────────────────────────
  const leaveVoice = useCallback(() => {
    if (!inVoiceRef.current) return

    stopSpeakingDetection()
    Object.keys(peersRef.current).forEach((uid) => closePeer(Number(uid)))

    localStreamRef.current?.getTracks().forEach((t) => t.stop())
    localStreamRef.current = null

    inVoiceRef.current = false
    mutedRef.current = true
    setInVoice(false)
    setMicError(null)
    sendMsg({ type: 'voice.leave' })
  }, [closePeer, sendMsg, stopSpeakingDetection])

  // ── Toggle mute ───────────────────────────────────────────────────────────
  const toggleMute = useCallback(() => {
    if (!localStreamRef.current) return
    const newMuted = !muted
    localStreamRef.current.getAudioTracks().forEach((t) => { t.enabled = !newMuted })
    mutedRef.current = newMuted
    setMuted(newMuted)
    // When muting, immediately signal speaking=false
    sendMsg({ type: 'voice.state_update', muted: newMuted, video: false, speaking: false })
  }, [muted, sendMsg])

  // ── Cleanup on unmount or channel switch ─────────────────────────────────
  useEffect(() => {
    return () => {
      if (inVoiceRef.current) leaveVoice()
    }
  }, [channelId, leaveVoice])

  return { inVoice, muted, micError, joinVoice, leaveVoice, toggleMute }
}
