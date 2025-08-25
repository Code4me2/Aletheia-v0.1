# Citation System Test Results

## Test Scenario
To properly test the citation system:

1. **Open lawyer-chat**: http://localhost:3000 (or through proxy)
2. **Select documents** from the Document Context panel (right side)
3. **Send a query** asking about those documents
4. **Check browser console** (F12 → Console tab) for debug output
5. **Click citation button** when it appears

## Expected Flow:
1. User selects documents in Document Context
2. Documents are sent with the user message as `documentContext`
3. AI responds with [DOC1], [DOC2] tags referencing the documents
4. Citation button appears (only if response contains [DOC] tags)
5. Click citation button → should open panel with cited documents

## Debug Information to Look For:
When clicking the citation button, the browser console should show:
```javascript
Citation clicked but no document context found {
  assistantMessage: {...},
  userMessage: {...},
  hasDocContext: [array of documents or undefined]
}
```

## Common Issues:
1. **No citation button appears**: AI response doesn't contain [DOC] tags
2. **Citation button doesn't work**: Document context not properly attached to user message
3. **Panel opens but empty**: Citation extraction failing

## Fixed Issues:
- ✅ Sequential ID assumption removed (was looking for `id - 1`)
- ✅ Now searches backwards for previous user message
- ✅ Added debug logging to identify issues

## Testing the Fix:
The fix changes how we find the corresponding user message:
- **Old**: Assumed assistant ID = user ID + 1
- **New**: Searches backwards from assistant message to find user message

This handles async timing issues where IDs aren't sequential.