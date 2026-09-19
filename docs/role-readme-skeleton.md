# Role README skeleton

Copy the part below to `roles/<name>/README.md` and replace the prose. Keep the
two `ANSIBLE_DOCS` markers exactly as they are: everything between them is
generated from `meta/argument_specs.yml` and `meta/main.yml` by `mise run docs`,
and anything written there by hand is overwritten. A README without the markers
fails the docs job.

---

# \<role\>

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
