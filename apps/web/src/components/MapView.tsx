import { Map, Marker } from '@vis.gl/react-google-maps';

interface Props {
  mapContainerRef: React.RefObject<HTMLDivElement | null>;
  mapCenter: google.maps.LatLngLiteral;
  mapZoom: number;
  onCameraChange: (ev: any) => void;
  mapType: 'satellite' | 'roadmap';
  setMapType: (type: 'satellite' | 'roadmap') => void;
  onClick: (ev: any) => void;
  onIdle: (ev: any) => void;
  pinLocation: google.maps.LatLngLiteral | null;
}

export const MapView = ({ 
  mapContainerRef, mapCenter, mapZoom, onCameraChange, 
  mapType, setMapType, onClick, onIdle, pinLocation 
}: Props) => (
  <div ref={mapContainerRef} className="relative flex-1 rounded-xl border-2 border-slate-200 overflow-hidden shadow-inner">
    <Map
      center={mapCenter}
      zoom={mapZoom}
      onCameraChanged={onCameraChange}
      mapTypeId={mapType}
      gestureHandling={'greedy'}
      disableDefaultUI={true}
      onClick={onClick}
      onIdle={onIdle}
    >
      {pinLocation && <Marker position={pinLocation} />}
    </Map>

    <div className="absolute top-4 right-4 flex bg-white rounded-md shadow-md border overflow-hidden z-10">
      <button 
        onClick={() => setMapType('satellite')} 
        className={`px-3 py-1 text-xs font-bold ${mapType === 'satellite' ? 'bg-indigo-600 text-white' : 'hover:bg-slate-50'}`}
      >
        Satellite
      </button>
      <button 
        onClick={() => setMapType('roadmap')} 
        className={`px-3 py-1 text-xs font-bold border-l ${mapType === 'roadmap' ? 'bg-indigo-600 text-white' : 'hover:bg-slate-50'}`}
      >
        Roadmap
      </button>
    </div>
  </div>
);