import React, { useState, useEffect } from "react";
import useCommonStore from "./../store/map";

const CountrySelector = () => {
  const countryCoordinates = {
    turkey: [38.0, 37.0],
    iraq: [43.5, 33.0],
    nepal: [85.2, 28.1],
    mexico: [-98.2, 19.0],
    usa: [-119.0, 37.0],
  };

  const countryBounds = {
    nepal: { minlat: 26.3, maxlat: 30.4, minlon: 80.0, maxlon: 88.2 },
    turkey: { minlat: 35.0, maxlat: 43.0, minlon: 25.0, maxlon: 45.0 },
    iraq: { minlat: 29.0, maxlat: 38.0, minlon: 38.0, maxlon: 49.0 },
    mexico: { minlat: 14.5, maxlat: 32.7, minlon: -118.4, maxlon: -86.7 },
    usa: { minlat: 32.5, maxlat: 42.0, minlon: -124.5, maxlon: -114.0 },
  };

  const { setMapboxCenter, setMapboxCountry, setCountryBounds } =
    useCommonStore();

  const [selectedCountry, setSelectedCountry] = useState("nepal");

  const handleChange = (event) => {
    const selected = event.target.value;
    setSelectedCountry(selected);
  };

  useEffect(() => {
    setMapboxCenter(countryCoordinates[selectedCountry]);
    setMapboxCountry(selectedCountry);
    setCountryBounds(countryBounds[selectedCountry]);
  }, [selectedCountry]);
  return (
    <div>
      <label htmlFor="dropdown">Choose a country:</label>
      <select id="dropdown" value={selectedCountry} onChange={handleChange}>
        <option value="nepal">Nepal</option>
        <option value="turkey">Turkey</option>
        <option value="iraq">Iraq</option>
        <option value="mexico">Mexico</option>
        <option value="usa">USA</option>
      </select>
    </div>
  );
};

export default CountrySelector;
