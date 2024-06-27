# AnimePlayer API

This repository contains the API for [AnimePlayer](https://github.com/Semolik/AnimePlayer), a platform for streaming anime. The API provides various endpoints for accessing anime content and metadata.

## Getting Started

### Prerequisites

Ensure you have the following installed on your system:

-   Docker
-   Docker Compose

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/YourUsername/AnimePlayer-API.git
    cd AnimePlayer-API
    ```

2. Copy the `.env.example` file to .env and fill in the necessary values:
    ```bash
    cp .env.example .env
    ```
3. Update the `.env` file with the required configuration parameters.

### Running the API

To start the API using Docker, run the following command:

    docker-compose up --build

### Parsers

Parsers for fetching anime data are located in the src/parsers directory. You can add or modify parsers as needed to support different sources or improve the existing ones. <b>Modules within the parsers directory are imported automatically</b>, ensuring that any new parsers added to this directory are immediately available for use without additional configuration.

### Usage

Once the API is running, you can access the endpoints via http://localhost:8000.
