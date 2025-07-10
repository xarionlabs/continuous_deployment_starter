# Troubleshooting

## Service Not Found Errors After Release

If you encounter "service not found" errors after a release, the issue is likely with Podman Quadlet not being able to parse the container configurations properly.

### Debugging Quadlet Configuration

Run the following command on the server to check if Quadlet can parse the containers and convert them to services:

```bash
/usr/libexec/podman/quadlet --dryrun --user $XDG_CONFIG_HOME/containers/systemd/
```

This command will:
- Run Quadlet in dry-run mode
- Show any parsing errors in the container configurations
- Display the systemd service files that would be generated
- Help identify configuration issues before they cause runtime problems

### Common Issues
- Invalid container configuration syntax
- Missing required fields in `.container` files
- Incorrect file permissions on configuration files
- Missing dependencies between services