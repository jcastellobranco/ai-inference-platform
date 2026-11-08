# ATLAS UI primitives

Use `Field.Root` with `Field.Label` and a native control. Labels and control IDs are connected by context. The native select retains keyboard navigation and screen-reader behavior.

```tsx
<Field.Root id="mode">
  <Field.Label>Execution mode</Field.Label>
  <Select.Control value={mode} onChange={event => setMode(event.target.value)}>
    <Select.Option value="tools">MCP tools</Select.Option>
    <Select.Option value="research">Research</Select.Option>
  </Select.Control>
</Field.Root>
```

For validation, set `invalid` on `Field.Root` and render `Field.ErrorMessage`. Use `Input` or `Textarea` within the same field. Buttons use a simple variant prop, not compound composition.

Do not create custom popover/listbox logic for a simple select: native controls are accessible and predictable. Shared styles live under `.ui-*` selectors in `style.css`.
