/**
 * EmojiPickerLazy — the dynamically-loaded chunk.
 *
 * Imported via React.lazy() in EmojiPicker.jsx so that @emoji-mart/react
 * and the ~800 KB emoji data file are excluded from the initial JS bundle.
 */
import Picker from '@emoji-mart/react'
import data from '@emoji-mart/data'

export default function EmojiPickerLazy({ onEmojiSelect, defaultSkin }) {
  return (
    <Picker
      data={data}
      theme="dark"
      set="native"
      onEmojiSelect={onEmojiSelect}
      skinTonePosition="search"
      previewPosition="none"
      locale="en"
      perLine={7}
      maxFrequentRows={2}
      skin={defaultSkin}
    />
  )
}
