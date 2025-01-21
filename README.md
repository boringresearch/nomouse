# NoMouse

NoMouse is an intelligent automation tool that enables keyboard-driven control of your computer, integrating with Vimium for enhanced browser navigation capabilities.

## Features

- AI-powered action execution
- Seamless integration with Vimium for browser control
- Region-based screen interaction
- Keyboard-driven interface

## Prerequisites

- Python 3.x
- Vimium browser extension
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nomouse.git
cd nomouse
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY=your_api_key_here
export ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

1. Start the application:
```bash
python main.py
```

2. Use keyboard shortcuts to interact with the tool:
   - Select regions on screen
   - Execute actions
   - Control browser navigation

## Components

- `action_executor.py`: Handles the execution of AI-powered actions
- `region_selector.py`: Manages screen region selection
- `vimium_controller.py`: Interfaces with the Vimium browser extension
- `constants.py`: Contains configuration constants

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.