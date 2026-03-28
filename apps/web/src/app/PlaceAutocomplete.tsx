import usePlacesAutocomplete, {
  getGeocode,
  getLatLng,
} from "use-places-autocomplete";

interface Props {
  onAddressSelect: (coords: { lat: number; lng: number }) => void;
}

export const PlaceAutocomplete = ({ onAddressSelect }: Props) => {
  const {
    ready,
    value,
    suggestions: { status, data },
    setValue,
    clearSuggestions,
  } = usePlacesAutocomplete({
    requestOptions: {
      componentRestrictions: { country: "ph" },
    },
    debounce: 300,
  });

  const handleSelect = async (address: string) => {
    setValue(address, false);
    clearSuggestions();

    try {
      const results = await getGeocode({ address });
      const { lat, lng } = await getLatLng(results[0]);
      onAddressSelect({ lat, lng });
    } catch (error) {
      console.error("Error fetching coordinates:", error);
    }
  };

  return (
    <div className="relative w-full">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={!ready}
        className="w-full pl-10 pr-4 py-2 bg-slate-50 border text-black placeholder-gray border-slate-200 rounded-md focus:ring-2 focus:ring-indigo-500 outline-none"
        placeholder="Search Barangay or City..."
      />
      
      {/* Suggestions List */}
      {status === "OK" && (
        <ul className="absolute z-50 w-full bg-white border border-slate-200 mt-1 rounded-md shadow-lg max-h-60 overflow-auto">
          {data.map(({ place_id, description }) => (
            <li
              key={place_id}
              onClick={() => handleSelect(description)}
              className="px-4 py-2 hover:bg-indigo-50 cursor-pointer text-sm text-slate-700 border-b border-slate-50 last:border-0"
            >
              {description}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};