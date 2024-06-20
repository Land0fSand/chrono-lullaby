# ChronoLullaby

ChronoLullaby is a service that provides subscription audio services from YouTube to Telegram groups.

## Features

- Subscribes to YouTube channels and downloads new videos as audio files.
- Sends the downloaded audio files to a specified Telegram group at regular intervals.

## Setup

1. Clone the repository.
2. Install the required Python packages using the `requirements.txt` or `environment.yml` file.
3. Set up your environment variables in a `.env` file. You will need to provide your Telegram bot token and the chat ID of the Telegram group where the audio files will be sent.
4. Run the `main.py` script to start the service.

## Usage

- To add a new YouTube channel to the subscription list, add the channel's name to the `channels.txt` file manually for now.


## License

This project is licensed under the terms of the GNU General Public License. For more information, see the [LICENSE](LICENSE) file.