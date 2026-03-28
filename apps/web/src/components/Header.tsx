import { Leaf, Thermometer } from 'lucide-react';

export const Header = () => (
  <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-slate-200 z-10">
    <div className="flex items-center gap-2 bg-slate-800 text-white px-4 py-2 rounded-md font-bold italic">
      <Leaf size={20} className="text-green-400" />
      CITY SENTINEL
    </div>
    <nav className="flex items-center gap-6">
      <button className="flex items-center gap-2 text-indigo-600 border-b-2 border-indigo-600 pb-1 font-medium">
        <Thermometer size={18} /> Heat Map
      </button>
    </nav>
    <div className="flex gap-3">
      <button className="px-4 py-2 text-sm font-medium border border-slate-300 rounded-md hover:bg-slate-50">Support</button>
      <button className="px-4 py-2 text-sm font-medium bg-slate-800 text-white rounded-md hover:bg-slate-700">Account</button>
    </div>
  </header>
);