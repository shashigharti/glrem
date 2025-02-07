import React, { useState } from "react";
import DatePicker from "react-datepicker";

const DateSelector = () => {
  const [startDate, setStartDate] = useState(new Date());

  const handleChange = (date) => {
    if (date) {
      setStartDate(date);
    }
  };

  return (
    <div className="container">
      <DatePicker
        selected={startDate}
        onChange={handleChange}
        dateFormat="yyyy/MM/dd"
        className="form-control"
        placeholderText="Click to select a date"
      />
    </div>
  );
};

export default DateSelector;
