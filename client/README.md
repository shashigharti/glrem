# GLREM App

## Setup

1. Navigate to the `client` directory:

   ```bash
   cd client
   ```

2. Install the dependencies:

   ```bash
   npm install
   ```

## Development

To start the development server, run the following command:

```bash
npm run dev
```

## Linting and Formatting

### Linting

To check for code issues, run the following command:

```bash
npm run lint
```

### Formatting

To check for code issues, run the following command:

```bash
npm run format
```

### ENV

Create a .env file and set the environment variables as
follows:

```bash
VITE_APP_ENDPOINT=http://localhost/:8000
VITE_APP_URL=http://localhost:5173/
VITE_REGION=us-east-1
VITE_BUCKET_NAME=glrem-sentinel1-slc
VITE_ACCESS_KEY_ID=AKIARWILO5L446IG2
VITE_SECRET_ACCESS_KEY=lYJYWg00kUqlIHlK
VITE_MAPBOX_TOKEN=pk.eyJ1Ijoic2hhc2hpZ2hhcnR
```
