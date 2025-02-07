export const isValidBlob = (blobUrl) => {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.src = blobUrl;

    image.onload = () => {
      resolve(true);
    };

    image.onerror = () => {
      resolve(false);
    };
  });
};

export const generateEventId = (event, etype = "earthquake") => {
  let eventid = 1;
  if (etype === "earthquake") {
    eventid = event.id;
  }
  return eventid;
};

export const generateFilename = (analysis = "intf", etype = "earthquake") => {
  let filename = `${etype}-${analysis}`;
  return filename;
};
