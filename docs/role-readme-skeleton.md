# Role README skeleton

Copy the block below to `roles/<name>/README.md`, replace the prose, and run
`mise run docs`.

Keep the two `ANSIBLE_DOCS` markers exactly as they are. Everything between them
is generated from `meta/argument_specs.yml` and `meta/main.yml`, and anything
written there by hand is overwritten. A README without the markers fails the
docs job, because aar-doc replaces the marker lines themselves and has nowhere
to put the block.

The skeleton is fenced rather than written out as live Markdown: it has its own
level-1 heading, and two level-1 headings in one document is a markdownlint
error. Fencing it also makes it obvious what you are meant to copy.

````markdown
# <role>

One sentence on what the role does, in the user's terms.

A short paragraph on how it behaves: what it creates, what it changes, and
anything it removes. Say the surprising parts out loud.

## Requirements

- What has to be true of the managed host.
- Anything the role does not install for you.

## Example playbook

```yaml
- hosts: servers
  roles:
    - role: ohioit.roles.<role>
      vars:
        <role>_something: value
```

<!-- BEGIN_ANSIBLE_DOCS -->
<!-- END_ANSIBLE_DOCS -->

## License

GNU General Public License v3.0 or later.
````
