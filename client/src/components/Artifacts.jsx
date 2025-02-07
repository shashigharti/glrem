import React, { useState, useEffect } from "react";
import { S3Client, ListObjectsV2Command } from "@aws-sdk/client-s3";

const BUCKET_NAME = "guardian-sentinel1-slc";
const REGION = "us-east-1";
const ACCESS_KEY_ID = "AKIARWILO5L446IG244G";
const SECRET_ACCESS_KEY = "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";

const s3 = new S3Client({
  region: REGION,
  credentials: {
    accessKeyId: ACCESS_KEY_ID,
    secretAccessKey: SECRET_ACCESS_KEY,
  },
});

const ArtifactList = () => {
  const [images, setImages] = useState([]);

  // Fetch the list of images from S3 bucket
  useEffect(() => {
    const fetchImages = async () => {
      const params = {
        Bucket: BUCKET_NAME,
      };

      try {
        const command = new ListObjectsV2Command(params);
        const data = await s3.send(command);

        const imageFiles = data.Contents?.filter((item) =>
          item.Key?.endsWith(".tif"),
        ); // Filter only .tif files
        setImages(imageFiles || []);
      } catch (error) {
        console.error("Error fetching images from S3:", error);
      }
    };

    fetchImages();
  }, []);

  return (
    <div className="image-list">
      <div className="list-group">
        {images.length === 0 ? (
          <p>No images found in the S3 bucket.</p>
        ) : (
          images.map((image) => (
            <div
              className="list-group-item d-flex justify-content-between align-items-center"
              key={image.Key}
            >
              <div className="d-flex align-items-center">
                <span>{image.Key}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ArtifactList;
