import React, { useState } from "react";

const FileList = ({ handleLayerClick }) => {
  const files = ["intf.tif", "corr.tif"];
  const [selectedFiles, setSelectedFiles] = useState([]);

  const handleCheckboxChange = (fileName, checked) => {
    setSelectedFiles((prevSelectedFiles) => {
      const updatedSelectedFiles = checked
        ? [...prevSelectedFiles, fileName]
        : prevSelectedFiles.filter((file) => file !== fileName);
      handleLayerClick(fileName, checked);
      return updatedSelectedFiles;
    });
  };

  return (
    <div>
      <ul style={{ listStyleType: "none", padding: 0 }}>
        {files.map((file) => (
          <li key={file} style={{ marginBottom: "8px" }}>
            <input
              type="checkbox"
              id={file}
              checked={selectedFiles.includes(file)}
              onChange={(e) => handleCheckboxChange(file, e.target.checked)}
            />
            <label htmlFor={file} style={{ marginLeft: "10px" }}>
              {file}
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FileList;
