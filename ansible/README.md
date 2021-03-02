This uses a typical ansible setup:

  - https://docs.ansible.com/ansible/latest/user_guide/sample_setup.html
  - https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html

To get started:

    pipenv run ansible-playbook --check --diff --inventory inventory.yml --ask-become-pass site.yml

to show what changes would be made; remove `--check` to apply them.

To view the documentation for an ansible module, you can use the
`ansible-doc` command, e.g., `ansible-doc user` inside the pipenv.
