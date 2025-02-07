const AnalysisTable = ({
  files,
  handleRegenerateButtonClick,
  handleAddLayerButtonClick,
}) => {
  const renderStatusIcon = (status) => {
    if (status === "processing") {
      return (
        <i className="bi bi-arrow-repeat text-warning" title="Processing"></i>
      );
    } else if (status === "complete") {
      return (
        <i className="bi bi-check-circle text-success" title="Complete"></i>
      );
    }
    return null;
  };

  return (
    <table className="table">
      <thead>
        <tr>
          <th>Event ID</th>
          <th>Location</th>
          <th>Latitude</th>
          <th>Longitude</th>
          <th>Filename</th>
          <th>Type</th>
          <th>Analysis</th>
          <th>Date</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {files.map((file, index) => (
          <tr key={index}>
            <td>{file.eventid}</td>
            <td>{file.location}</td>
            <td>{file.latitude}</td>
            <td>{file.longitude}</td>
            <td>{file.filename}</td>
            <td>{file.eventtype}</td>
            <td>{file.analysis}</td>
            <td>{file.date}</td>
            <td>{renderStatusIcon(file.status)}</td>
            <td>
              <button
                onClick={handleRegenerateButtonClick}
                style={{ marginRight: "5px" }}
              >
                Regenerate
              </button>
              <button
                onClick={(event) =>
                  handleAddLayerButtonClick(event, file.eventid, file.filename)
                }
                style={{ marginRight: "5px" }}
              >
                Add to Layer
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default AnalysisTable;
