"use client";

import { useEffect, useState } from "react";

export default function InstallPWA() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      // Prevent the browser's default bar from showing immediately
      e.preventDefault();
      // Stash the event so it can be triggered later.
      setDeferredPrompt(e);
      setIsVisible(true);
    };

    window.addEventListener("beforeinstallprompt", handler);

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;

    // Show the native install prompt
    deferredPrompt.prompt();

    // Wait for the user to respond to the prompt
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === "accepted") {
      console.log("User accepted the Dunam Velocity install");
    }
    
    setDeferredPrompt(null);
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 bg-blue-600 text-white p-4 rounded-lg shadow-2xl flex justify-between items-center z-50">
      <div>
        <p className="font-bold">Install Dunam Velocity</p>
        <p className="text-sm">Access your trading dashboard from your home screen.</p>
      </div>
      <button 
        onClick={handleInstallClick}
        className="bg-white text-blue-600 px-4 py-2 rounded-md font-bold text-sm"
      >
        Install
      </button>
    </div>
  );
}