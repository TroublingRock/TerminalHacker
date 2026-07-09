# Easy install — Security Simulator

No terminal commands needed. Pick your platform after downloading the game folder (GitHub **Code → Download ZIP**, or clone).

## Windows

1. Unzip the download.
2. Double-click **`Play Security Simulator.vbs`** (recommended — no black command window).
   - Or double-click **`Play Security Simulator.bat`** if you prefer to see install progress.
3. If Python is missing, the launcher offers to install it automatically via winget (~25 MB).
4. The game opens in the Ubuntu-style desktop GUI.

**CLI only:** run `Play Security Simulator.bat --cli` from a terminal, or after Python is installed: `python main.py --cli`

## macOS

1. Unzip the download.
2. Double-click **`Play Security Simulator.command`**.
   - First launch: right-click → **Open** if macOS blocks unknown developers.
3. If Python is missing, the launcher opens python.org or offers Homebrew install.

## Linux

1. Unzip the download.
2. Run once in a terminal to make the launcher executable (only needed after ZIP download):
   ```bash
   chmod +x play-security-simulator.sh "Play Security Simulator.command"
   ```
3. Double-click **`play-security-simulator.sh`** in your file manager,  
   **or** double-click **`Security Simulator.desktop`** to add a menu shortcut.
4. If Python or `python3-tk` is missing, the launcher prompts to install (admin password).

## Requirements

- **Python 3.10+** (auto-installed on Windows when possible)
- **Tkinter** for the GUI (bundled on Windows/macOS; `python3-tk` on Linux)
- No pip packages required for core gameplay

## Advanced / developers

```bash
python3 main.py          # GUI
python3 main.py --cli    # terminal only
python3 launch/bootstrap.py
```

Saves live in `~/.terminalhacker/save.json`.
