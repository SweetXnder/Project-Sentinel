"use client";
import React, { useEffect, useRef } from "react";
import { useMapsLibrary } from "@vis.gl/react-google-maps";

interface Props {
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  onAddressSelect: (
    coords: { lat: number; lng: number },
    address: string
  ) => void;
  coordsText: string;
  address: string;
  setAddress: (value: string) => void;
}

export const SearchArea = ({
  onSubmit,
  onAddressSelect,
  coordsText,
  address,
  setAddress,
}: Props) => {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const places = useMapsLibrary("places");

  useEffect(() => {
    if (!places || !inputRef.current) return;

    const autocomplete = new places.Autocomplete(inputRef.current, {
      componentRestrictions: { country: "ph" },
      fields: ["geometry", "formatted_address", "name"],
    });

    autocomplete.addListener("place_changed", () => {
      const place = autocomplete.getPlace();

      if (!place.geometry?.location) return;

      const lat = place.geometry.location.lat();
      const lng = place.geometry.location.lng();

      const coords = { lat, lng };
      const addressName =
        place.formatted_address || place.name || "Selected location";

      setAddress(addressName);
      onAddressSelect(coords, addressName);
    });
  }, [places]);

  return (
    <section className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
      <form onSubmit={onSubmit} className="flex items-center gap-2">
        <input
          ref={inputRef}
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          type="text"
          placeholder="Search location..."
          className="flex-1 px-3 py-2 border border-slate-300 rounded-md outline-none focus:ring-2 focus:ring-indigo-500"
        />

        <button
          type="submit"
          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          Find
        </button>
      </form>

      <p className="mt-2 text-sm text-slate-700">
        Selected coords:{" "}
        <span className="font-bold text-indigo-600">
          {coordsText || "None yet"}
        </span>
      </p>
    </section>
  );
};