const config = {
  mapBoxToken: import.meta.env.VITE_MAPBOX_TOKEN,
  bucketName: import.meta.env.VITE_BUCKET_NAME,
  region: import.meta.env.VITE_REGION,
  accessAWSKeyID: import.meta.env.VITE_AWS_ACCESS_KEY_ID,
  secretAWSACCESSKEY: import.meta.env.VITE_AWS_SECRET_ACCESS_KEY,
};

export default config;
