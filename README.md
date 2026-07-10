
# SELinux Explorer
<br/>

SELinux Explorer is a utility designed to help developers explore and visualize SELinux policies, with a focus on Android SELinux at present. The project initially started as a command-line tool but has since evolved to include a graphical user interface (GUI) for better usability and to provide additional features such as filtering, generating custom output, and reusing data.

The tool supports the following file types:
- `file_contexts`
- `service_contexts`
- `vndservice_contexts`
- `hwservice_contexts`
- `property_contexts`
- `seapp_contexts`
- `*.te`

**Please note**: The tool is a work in progress and might have some issues or require performance improvements. We welcome any bug reports, suggestions, or contributions.

<br/>

## Use cases

- Threat assessment and cybersecurity analysis
    - Identify potential vulnerabilities in policies
    - Detect possible privilege escalation paths
- Android app development
    - Debug and optimize SELinux policies for custom apps
    - Verify proper policy configuration
- System administration
    - Audit and review SELinux policies
    - Improve system security and compliance
- Security research
    - Analyze and understand complex policy structures
    - Develop new security solutions and enhancements
- Documentation
<br/>

### Screenshots of the GUI and the generated output
#### GUI
![GUI](./screenshots/gui.png)
<br/>
#### Outputs
![GUI](./screenshots/top_view_1.png)
<br/>
![GUI](./screenshots/sequential_1.png)

<br/>

## Dependencies

To run SELinux Explorer, you need to have Python 3.12 and some other packages installed on your local machine:

- Python 3.12 or newer
- PythonIsPython3
- Graphviz
- PyQt5
- Dataclass-wizard
- Dataclasses

## Installation
#### Note : The 1st & 2nd steps can be skipped by running the `setup.sh` script.
```
./setup.sh
```
&ensp;

1. Install Python 3.12 or a newer version, PythonIsPython3, Graphviz, and PyQt5:

```
sudo apt install python3.12 python-is-python3 graphviz python3-pyqt5 -y
```
&ensp;


2. Install python packages

```
pip install -r requirements.txt
```

&ensp;

3. Clone the project and its submodule:

```
git clone https://github.com/Heydarchi/SELinux-Explorer.git
```
&ensp;

4. Inside the cloned folder, run the following command to update the submodule:

```
git submodule update --init --recursive
```
<br/>

## How to Run the GUI

1. Change to the `app` directory:

```
cd app
```

2. Run the main.py script:

```
python main.py
```
<br/>

## Docker

Docker is the easiest way to run SELinux Explorer without installing any system
dependencies manually. The image bundles Python 3.12, PyQt5, Graphviz, Java 21,
and PlantUML.

### Build the image

```bash
git clone https://github.com/cpac-heydarchi/SELinux-Explorer.git
cd SELinux-Explorer
git submodule update --init --recursive
docker build -t selinux-explorer .
```

### Run – with a local X11 display (Linux)

Docker containers have a different hostname than the host, so the standard
`~/.Xauthority` file is rejected. A docker-compatible auth cookie must be
created **once per login session** and the variable must be set **in the same
shell** as the `docker run` command.

```bash
# 1. Create a wildcard-hostname auth cookie (once per session)
XAUTH_DOCKER=/tmp/.docker.xauth
touch $XAUTH_DOCKER
xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f $XAUTH_DOCKER nmerge -

# 2. Run the container in the same shell (XAUTH_DOCKER must still be set)
docker run --rm -it \
  -e DISPLAY=$DISPLAY \
  -e XAUTHORITY=/tmp/.Xauth \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $XAUTH_DOCKER:/tmp/.Xauth:ro \
  -v $(pwd)/policy:/policy \
  selinux-explorer
```

> **Tip:** add `export XAUTH_DOCKER=/tmp/.docker.xauth` to `~/.bashrc` so the
> variable survives across terminal sessions. You still need to re-run the
> `xauth nlist …` cookie-generation command after each login.

### Run – headless (no display required)

Starts a virtual framebuffer (Xvfb) inside the container automatically. Useful
on servers, CI, or WSL without an X server:

```bash
docker run --rm -it \
  -v $(pwd)/policy:/policy \
  selinux-explorer headless
```

### Run – tests only

```bash
docker run --rm selinux-explorer pytest app/test -q
```

### Mount your policy files

Pass your policy directory as a volume so the tool can analyse it:

```bash
docker run --rm -it \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /path/to/your/policy:/policy \
  selinux-explorer
```

Inside the GUI, add `/policy` as a source path.
<br/>

## Contributing

Thank you for your interest in contributing to SELinux Explorer! We welcome and appreciate any contributions, whether it's bug reports, feature requests, code, documentation, or testing. Please refer to our [CONTRIBUTION.md](CONTRIBUTING.md) file for detailed guidelines on how to set up your development environment, check code style, run tests, and submit your changes.

## Features and TODOs

This project is under active development, and we're continuously working on improving and expanding its functionality. For a detailed list of features and tasks that we're planning to implement, please refer to the [TODO List](TODO.md) file. We welcome your contributions and feedback, so feel free

## Bug Reports:

If you encounter any issues or bugs while using SELinux Explorer, we encourage you to report them, so we can address and fix them promptly. Please create a new issue using our [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md) and provide all the necessary details to help us reproduce and understand the problem. Your feedback is invaluable in helping us maintain the tool's reliability and stability.

## Feature Requests:

We're always looking to improve and expand the functionality of SELinux Explorer. If you have a suggestion for a new feature or an enhancement to an existing one, we'd love to hear from you. Please create a new issue using our [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md) and provide a clear and concise description of your idea, including the problem it aims to solve and the benefits it would bring. Your input is essential in shaping the future development and direction of the project.

## License

This project is released under the [Apache 2.0 License](LICENSE).

