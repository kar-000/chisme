import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * useVoiceRecorder — records audio using MediaRecorder.
 *
 * @param {function} onRecorded - called with (blob, durationSecs) when a
 *   recording is successfully stopped.  Pass a stable (useCallback) reference.
 *
 * @returns {{ state, startRecording, stopRecording, cancelRecording }}
 *   state: 'idle' | 'recording'
 */
export default function useVoiceRecorder(onRecorded) {
  const [state, setState] = useState('idle')
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const startTimeRef = useRef(null)

  // Keep the callback ref up-to-date without re-creating the hook functions.
  const onRecordedRef = useRef(onRecorded)
  useEffect(() => { onRecordedRef.current = onRecorded }, [onRecorded])

  const startRecording = useCallback(async () => {
    if (state === 'recording') return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // Pick the best available MIME type
      const mimeType =
        MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm'
        : ''

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {})
      mediaRecorderRef.current = recorder
      chunksRef.current = []
      startTimeRef.current = Date.now()

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        const elapsed = Math.round((Date.now() - startTimeRef.current) / 1000)
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        stream.getTracks().forEach((t) => t.stop())
        streamRef.current = null
        setState('idle')
        onRecordedRef.current?.(blob, elapsed)
      }

      recorder.start()
      setState('recording')
    } catch (err) {
      console.error('[useVoiceRecorder] Could not start recording:', err)
    }
  }, [state])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  const cancelRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current
    if (recorder) {
      recorder.onstop = () => {} // discard the blob
      if (recorder.state === 'recording') recorder.stop()
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    chunksRef.current = []
    setState('idle')
  }, [])

  return { state, startRecording, stopRecording, cancelRecording }
}
