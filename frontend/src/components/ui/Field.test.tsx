import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { Button, Field, Input, Select, Textarea } from './index';

describe('composable UI fields', () => {
  it('connects label and native select with an explicit id', () => {
    const html = renderToStaticMarkup(
      <Field.Root id="mode"><Field.Label>Execution mode</Field.Label>
        <Select.Control defaultValue="tools"><Select.Option value="tools">Tools</Select.Option></Select.Control>
      </Field.Root>,
    );
    expect(html).toContain('for="mode"');
    expect(html).toContain('id="mode"');
    expect(html).toContain('class="ui-select"');
    expect(html).toContain('value="tools"');
  });

  it('connects error feedback to an invalid input', () => {
    const html = renderToStaticMarkup(
      <Field.Root id="name" invalid><Field.Label>Name</Field.Label>
        <Input /><Field.ErrorMessage>Required</Field.ErrorMessage>
      </Field.Root>,
    );
    expect(html).toContain('aria-invalid="true"');
    expect(html).toContain('aria-describedby="name-error"');
    expect(html).toContain('id="name-error"');
    expect(html).toContain('role="alert"');
  });

  it('supports textarea and defaults button type to button', () => {
    const html = renderToStaticMarkup(
      <><Field.Root id="task"><Field.Label>Task</Field.Label><Textarea rows={3} /></Field.Root>
        <Button variant="secondary">Cancel</Button></>,
    );
    expect(html).toContain('id="task"');
    expect(html).toContain('rows="3"');
    expect(html).toContain('type="button"');
    expect(html).toContain('button-secondary');
  });
});
