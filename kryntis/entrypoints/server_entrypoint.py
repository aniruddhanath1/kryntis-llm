"""Server Entrypoint implementation."""

import uvicorn
from kryntis.constants.system_defaults import DEFAULT_HOST, DEFAULT_PORT

def main_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    uvicorn.run("kryntis.service.app:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main_server()
