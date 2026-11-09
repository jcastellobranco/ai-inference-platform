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

## Repository-wide usage

Use `Button` for all interactive buttons, including specialized actions (`variant="unstyled"` preserves an existing class without adding default button styles). Use `Field.Root` with `Input`, `Textarea`, or `Select.Control` for form controls. `FileInput` wraps the native browser file picker and supports refs. `Dialog.Root` and `Dialog.Content` compose modal structure. `Table.Scroll`, `Table.Root`, `Table.Header`, `Table.Body`, `Table.Row`, `Table.Head`, and `Table.Cell` compose tables.

`Tabs` currently implements **segmented buttons** with `role="group"` and `aria-pressed`, not WAI-ARIA tab panels. Use it for mutually exclusive modes and filters, not for actual tab-panel navigation.

Semantic structural tags such as `section`, `nav`, `form`, `article`, and `div` remain native: wrapping every HTML tag adds indirection without shared behavior.

Run `npm run check` from `frontend/` to audit raw interactive tags, run unit tests, and compile. The UI audit prevents new raw controls outside `components/ui`. It does not replace browser-based visual and accessibility tests.
