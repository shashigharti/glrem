import { getRequest } from "../apis/client";

export const fetchLayer = async (eventid, filename) => {
  try {
    const endpoint = `${import.meta.env.VITE_APP_ENDPOINT}/geospatial/get-files`;
    console.log(`Fetching data from: ${endpoint}`);

    const response = await getRequest(endpoint, { eventid, filename });

    if (!response || !response.png_base64 || !response.geojson) {
      throw new Error("Invalid response data: Missing png_base64 or geojson");
    }

    const { png_base64, geojson } = response;

    const imageBlob = new Blob(
      [
        new Uint8Array(
          atob(png_base64)
            .split("")
            .map((c) => c.charCodeAt(0)),
        ),
      ],
      { type: "image/jpeg" },
    );

    const imageObjectURL = URL.createObjectURL(imageBlob);

    return { filename, image: imageObjectURL, metadata: geojson };
  } catch (err) {
    console.error(`Failed to fetch layer for filename "${filename}":`, err);
    return null;
  }
};
