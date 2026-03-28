"use client";
import React, { useState } from 'react';
import { APIProvider, Map, Marker } from '@vis.gl/react-google-maps';
import { Download, Share2, Leaf, Map as MapIcon, Satellite, Loader2 } from 'lucide-react';

import { LeftSidebar } from '../components/LeftSidebar';
import { Header } from '../components/Header';
import { SearchArea } from '../components/SearchArea';
import { RightSidebar } from '@/components/RightSidebar';
import { useSentinelData } from '../hooks/useSentinelData';

const GOOGLE_MAPS_API_KEY = 'AIzaSyBaVYw5XO6M6Y4rtf0-I8yNQnPkkqsk9oM';

export default function CitySentinelDashboard() {
  const [mapType, setMapType] = useState<'satellite' | 'roadmap'>('satellite');
  const [address, setAddress] = useState('');
  const [mapCenter, setMapCenter] = useState({ lat: 14.6760, lng: 121.0437 });
  const [mapZoom, setMapZoom] = useState(14);
  const [pinLocation, setPinLocation] = useState<google.maps.LatLngLiteral | null>(null);
  const [coordsText, setCoordsText] = useState('');
  
  const { data, loading, analyzeLocation } = useSentinelData();

  const handleAddressSelect = (coords: { lat: number; lng: number }, addressName: string) => {
    setMapCenter(coords);
    setMapZoom(17);
    setPinLocation(coords);
    setCoordsText(`${coords.lat.toFixed(6)}, ${coords.lng.toFixed(6)}`);
    setAddress(addressName);
    analyzeLocation(coords.lat, coords.lng);
  };

  return (
    <APIProvider apiKey={GOOGLE_MAPS_API_KEY} libraries={['places']}>
      <div className="flex flex-col h-screen w-full bg-[#f8faf7] text-emerald-950 font-sans overflow-hidden">
        <Header />
        
        <div className="flex flex-1 overflow-hidden">
          <LeftSidebar 
            dvi={data?.metadata.NDVI?.toString() || "[NaN]"}
            ndwi={data?.metadata.NDWI?.toString() || "[NaN]"}
            ndbi={data?.metadata.NDBI?.toString() || "[NaN]"}
            ndmi={data?.metadata.NDMI?.toString() || "[NaN]"}
          />

          <main className="flex-1 flex flex-col p-4 md:p-6 space-y-4 bg-transparent min-w-0">
            {/* Header Card */}
            <div className="flex flex-col md:flex-row md:items-center justify-between bg-white p-4 rounded-2xl shadow-sm border border-emerald-100 gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-emerald-600 rounded-xl text-white shadow-lg shadow-emerald-100">
                  <Leaf size={20} />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-emerald-900 leading-tight">Ateneo Campus Urban Sustainability and Remote Sensing Assessment</h1>
                  <p className="text-[10px] text-emerald-600 font-bold uppercase tracking-widest">Environmental Intelligence</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold border border-emerald-200 text-emerald-700 rounded-xl hover:bg-emerald-50 transition-all">
                  <Download size={16} /> Export
                </button>
                <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 shadow-md transition-all active:scale-95">
                  <Share2 size={16} /> Share
                </button>
              </div>
            </div>

            {/* Search Section */}
            <div className="bg-white rounded-2xl shadow-sm border border-emerald-50 p-1">
              <SearchArea
                onSubmit={(e) => e.preventDefault()}
                onAddressSelect={handleAddressSelect}
                coordsText={coordsText}
                address={address}
                setAddress={setAddress}
              />
            </div>

            {/* Map Container - FIXED HEIGHT LOGIC */}
            <div className="flex-1 relative rounded-3xl overflow-hidden border-4 border-white shadow-2xl bg-emerald-50">
              <Map
                style={{ width: '100%', height: '100%' }}
                defaultCenter={mapCenter}
                center={mapCenter}
                defaultZoom={mapZoom}
                zoom={mapZoom}
                mapTypeId={mapType}
                onCameraChanged={(ev) => {
                   setMapCenter(ev.detail.center);
                   setMapZoom(ev.detail.zoom);
                }}
                onClick={(ev) => {
                  if (ev.detail.latLng) {
                    const latLng = ev.detail.latLng;
                    setPinLocation(latLng);
                    setCoordsText(`${latLng.lat.toFixed(6)}, ${latLng.lng.toFixed(6)}`);
                    analyzeLocation(latLng.lat, latLng.lng);
                  }
                }}
                disableDefaultUI={true}
              >
                {pinLocation && <Marker position={pinLocation} />}
              </Map>

              {/* Loading Overlay */}
              {loading && (
                <div className="absolute inset-0 bg-emerald-900/10 backdrop-blur-[2px] flex items-center justify-center z-10">
                  <div className="bg-white p-4 rounded-2xl shadow-xl flex items-center gap-3 border border-emerald-100">
                    <Loader2 className="animate-spin text-emerald-600" />
                    <span className="font-bold text-emerald-800">Analyzing Satellite Data...</span>
                  </div>
                </div>
              )}

              {/* Floating Eco-Controls */}
              <div className="absolute bottom-6 left-6 flex flex-col gap-2">
                <div className="bg-white/90 backdrop-blur p-1.5 rounded-2xl shadow-lg border border-emerald-100 flex flex-col gap-1">
                  <button 
                    onClick={() => setMapType('roadmap')}
                    className={`p-3 rounded-xl transition-all ${mapType === 'roadmap' ? 'bg-emerald-600 text-white shadow-md' : 'text-emerald-600 hover:bg-emerald-50'}`}
                    title="Roadmap View"
                  >
                    <MapIcon size={20} />
                  </button>
                  <button 
                    onClick={() => setMapType('satellite')}
                    className={`p-3 rounded-xl transition-all ${mapType === 'satellite' ? 'bg-emerald-600 text-white shadow-md' : 'text-emerald-600 hover:bg-emerald-50'}`}
                    title="Satellite View"
                  >
                    <Satellite size={20} />
                  </button>
                </div>
              </div>
            </div>
          </main>

          <RightSidebar />
        </div>
      </div>
    </APIProvider>
  );
}