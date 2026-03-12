# Windows + WSL2 Node Path

Use this path when the operator runs Windows 10/11 and wants to build and run a BoN node locally using WSL2 (Windows Subsystem for Linux 2).

This path was proven in this workspace on Windows 11 with WSL2 Ubuntu. The node runs inside WSL2; all agent commands execute in a WSL2 bash shell.

## When To Use It

Use the Windows path when:

- the operator's machine is Windows
- no Ubuntu server is provisioned
- the goal is to validate the workflow or run a local node for bug hunting
- the agent has access to WSL2 (e.g. via `wsl -e bash -c "..."`)

Do not treat this as the final production validator environment for 24/7 uptime.

## Prerequisites

- **Windows 10/11** with administrator access
- **WSL2** installed with Ubuntu (22.04 or newer)
- **~2500 EGLD** in the operator wallet plus gas
- **~10 GB** free disk for node build and state

## Install WSL2 (If Not Present)

From PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu
```

After installation, restart if prompted. Then open Ubuntu from the Start menu or run `wsl`.

To enable WSL2 as default for new distros:

```powershell
wsl --set-default-version 2
```

## Path Mapping

Windows paths map to WSL as follows:

- `C:\Users\<user>\Documents\...` → `/mnt/c/Users/<user>/Documents/...`
- Use forward slashes and escape spaces: `/mnt/c/Users/user/My\ Project/`

Example: workspace at `C:\Users\sheme\Documents\Dev\Supernova - Battle of Nodes` becomes:

```bash
/mnt/c/Users/sheme/Documents/Dev/Supernova\ -\ Battle\ of\ Nodes
```

## Agent Execution Context

**All agent commands must run inside WSL2.** Do not run `mxpy`, `go`, or node build commands in PowerShell or CMD.

From a Windows host, invoke WSL explicitly:

```bash
wsl -e bash -c "cd /mnt/c/path/to/workspace && mxpy --version"
```

Or open a WSL terminal and run commands directly.

## WSL2 Environment Setup

Inside WSL2 Ubuntu, install dependencies before on-chain or node steps:

```bash
# Update and install base tools
sudo apt-get update
sudo apt-get install -y git curl jq perl build-essential wget ca-certificates

# Install Go (BoN config uses 1.23.6)
GO_VERSION="1.23.6"
wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf "go${GO_VERSION}.linux-amd64.tar.gz"
rm "go${GO_VERSION}.linux-amd64.tar.gz"
export PATH=$PATH:/usr/local/go/bin
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc

# Install mxpy (Ubuntu 22+ may require --break-system-packages)
pip3 install --user --break-system-packages multiversx-sdk-cli
export PATH=$PATH:~/.local/bin
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc

# Install Python SDK for wallet derivation
pip3 install --user --break-system-packages multiversx-sdk-wallet multiversx-sdk-core
```

If `pip3 install --user` fails with "externally-managed-environment", add `--break-system-packages`.

## Proven Local Build Plan (Same as agent-node-local)

1. Clone the BoN config tag from `mx-chain-mainnet-config`.
2. Read `binaryVersion` from that config repo.
3. Clone `mx-chain-go` at the pinned BoN tag.
4. Build the node binary inside WSL2.
5. Build a runtime directory with:
   - config files from the config repo
   - `validatorKey.pem` in `config/`
   - `prefs.toml` patched with `NodeDisplayName = "<Name>BoN"`
6. Start the node with a local REST API and saved logs.
7. Wait for sync or restore a shard snapshot first.

## Proven Versions

- config tag: `v1.11.0.3-bon`
- config repo `binaryVersion`: `tags/v1.11.2-bon`
- config repo `goVersion`: `1.23.6`

## Reproducible Commands (WSL2)

These commands assume a workspace at `$WORKSPACE` (e.g. `/mnt/c/Users/user/BoN-workspace`):

```bash
cd "$WORKSPACE"
mkdir -p native-node
cd native-node

git clone --branch v1.11.0.3-bon https://github.com/multiversx/mx-chain-mainnet-config.git

BON_BINARY_TAG="$(sed 's#tags/##' mx-chain-mainnet-config/binaryVersion)"

git clone --branch "$BON_BINARY_TAG" https://github.com/multiversx/mx-chain-go.git

WORKDIR="$(pwd)"
mkdir -p "$WORKDIR/runtime/node-0/config" "$WORKDIR/runtime/node-0/logs" /tmp/go-build-bon /tmp/go-mod-bon

cp -R "$WORKDIR/mx-chain-mainnet-config/"* "$WORKDIR/runtime/node-0/config/"
cp "$WORKSPACE/.bon-keys/validatorKey.pem" "$WORKDIR/runtime/node-0/config/validatorKey.pem"

cd "$WORKDIR/mx-chain-go/cmd/node"
GOCACHE=/tmp/go-build-bon GOMODCACHE=/tmp/go-mod-bon go build \
  -o "$WORKDIR/runtime/node-0/node" \
  -ldflags="-X main.appVersion=$(git --git-dir "$WORKDIR/mx-chain-mainnet-config/.git" describe --tags --long --dirty)"
```

Patch the runtime config:

```bash
perl -0pi -e 's/NodeDisplayName = \".*?\"/NodeDisplayName = \"YourNodeBoN\"/' "$WORKDIR/runtime/node-0/config/prefs.toml"
perl -0pi -e 's/RedundancyLevel = .*/RedundancyLevel = 0/' "$WORKDIR/runtime/node-0/config/prefs.toml"
```

## Start Command

From the runtime directory:

```bash
cd "$WORKDIR/runtime/node-0"
./node \
  -use-log-view \
  -log-logger-name \
  -log-correlation \
  -log-level '*:DEBUG' \
  -rest-api-interface localhost:8080 \
  --display-name YourNodeBoN \
  --log-save \
  --port 41000
```

The node REST API at `localhost:8080` is accessible from Windows as `http://127.0.0.1:8080` (WSL2 forwards localhost).

## What Success Looks Like

Early success signals:

1. the process stays up inside WSL2
2. logs show the BoN version string
3. logs show peer connections
4. logs show `trie sync in progress`

Later success signals:

1. `curl http://127.0.0.1:8080/node/status` stops returning "node is starting"
2. `curl http://127.0.0.1:8080/node/heartbeatstatus` returns real heartbeat data
3. the node processes blocks after trie sync

## Snapshot Option

If full trie sync is too slow, use the published BoN shard snapshot from [bon-network-reference.md](bon-network-reference.md).

## Windows-Specific Notes

1. **mxpy PATH**: Ensure `~/.local/bin` is in PATH inside WSL. Use `~/.local/bin/mxpy` if the agent invokes commands without a login shell.
2. **Line endings**: If scripts fail with `\r` errors, run `sed -i 's/\r$//' script.sh` or ensure files use LF line endings.
3. **Firewall**: Windows Firewall may block incoming connections. For local-only node API, this is usually fine.
4. **WSL2 memory**: If the node build or run is slow, increase WSL2 memory in `%USERPROFILE%\.wslconfig` (requires `wsl --shutdown` to apply).

## Reference

This document extends [agent-node-local.md](agent-node-local.md) with Windows and WSL2 specifics. The build and runtime logic is identical; only the host OS and execution context differ.
