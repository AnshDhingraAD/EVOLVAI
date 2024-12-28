import { useState } from "react";
// import React from "react";


function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [resultImage, setResultImage] = useState(null); // State to store the processed image
  const [vehicleCount, setVehicleCount] = useState({});
  const [greenLightDuration, setGreenLightDuration] = useState(null);
  const [aqi, setAqi] = useState(null);

  // Handle file selection
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert("Please select an image to upload.");
      return;
    }

    setIsProcessing(true);

    const formData = new FormData();
    formData.append("files", selectedFile); // 'files' is the expected key on the backend
    formData.append("numEmergencyVehicles", 0); // Example: No emergency vehicles in this request

    try {
      // Send POST request to backend with CORS enabled
      const response = await fetch("http://localhost:8001/process_images", {
        method: "POST",
        body: formData,
        // Ensure 'cors' mode is set
        mode: "cors",
      });

      if (!response.ok) {
        throw new Error("Failed to upload image.");
      }

      const data = await response.json();
      console.log(data); // Process the response from the backend

      // Extract base64 image with bounding boxes from the response
      const processedImage = data.results[0]?.image_with_boxes;
      const result = data.results[0];
      

      if (processedImage) {
        setResultImage(`data:image/png;base64,${processedImage}`); // Store base64 image in state
      }
      setVehicleCount(result.vehicle_count);
      setGreenLightDuration(result.green_light_duration);
      setAqi(result.aqi);

      alert("Upload successful!");
    } catch (error) {
      console.error("Error during upload:", error);
      alert("An error occurred during upload.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <>
      <div className="bg-gray-800">
        <header className="relative gap-5 flex max-w-screen-xl flex-col overflow-hidden m-5 px-4 py-1 text-blue-900 md:mx-auto md:flex-row md:items-center">
          <div className="m-5 flex gap-20 items-center justify-between">
            <a
              href="#"
              className="flex cursor-pointer items-center whitespace-nowrap text-3xl font-black text-blue-500"
            >
              EVOLVE AI
            </a>
            <h1 className="cursor-pointer items-center whitespace-nowrap text-3xl font-black text-white mx-36">
              SMART TRAFFIC SYSTEM
            </h1>
          </div>
          <nav
            aria-label="Header Navigation"
            className="peer-checked:mt-8 peer-checked:max-h-56 flex max-h-0 w-full flex-col items-center justify-between overflow-hidden transition-all md:ml-24 md:max-h-full md:flex-row md:items-start"
          >
            <ul className="flex flex-col items-center space-y-2 md:ml-auto md:flex-row md:space-y-0">
              <li className="font-bold text-gray-100 md:mr-12">
                <a href="#">HOME</a>
              </li>
              <li className="text-gray-100 md:mr-12">
                <a href="#">FEATURES</a>
              </li>
            </ul>
          </nav>
        </header>

        <div className="mx-auto h-full px-4 py-28 md:py-38 sm:max-w-xl md:max-w-full md:px-24 lg:max-w-screen-xl lg:px-8">
          <div className="flex flex-col items-center justify-between lg:flex-row">
            <div>
              <div className="lg:max-w-xl lg:pr-5">
                <p className="flex text-sm uppercase text-gray-300">
                  AI TRAFFIC MANAGEMENT SYSTEM
                </p>
                <h2 className="mb-6 max-w-lg text-5xl font-bold leading-snug tracking-tight text-white sm:text-7xl sm:leading-snug">
                  Make your ride
                  <span className="my-1 inline-block border-b-8 border-white bg-orange-400 px-4 font-bold text-white m-28">
                    safer
                  </span>
                </h2>
                <p className="text-gray-400 text-2xl">
                  Upload Lane Image or Video to get the Green light Timing Based
                  on Vehicles Priority.
                </p>
              </div>
              <div className="mt-10 flex flex-col items-center md:flex-row">
                <input
                  type="file"
                  accept="image/*,video/*"
                  onChange={handleFileChange}
                  className="p-2 bg-blue-800 text-white rounded-md cursor-pointer"
                />
                <button
                  onClick={handleUpload}
                  disabled={isProcessing}
                  className="ml-4 bg-blue-800 text-white px-6 py-3 rounded-md font-medium tracking-wide shadow-md transition focus:outline-none hover:bg-blue-900"
                >
                  {isProcessing ? "Processing..." : "Upload"}
                </button>
              </div>
            </div>
            <div className="relative hidden lg:ml-42 lg:block lg:w-1/2">
              <div className="w-370 h-270 flex-wrap rounded-[2rem] mx-auto overflow-hidden rounded-tl-none rounded-br-none">
                {/* Use resultImage if available, otherwise show a default image */}
                <img
                  src={
                    resultImage ||
                    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRWS9hpDJJXRyrEY7y1vm5IIyiWs4Xn3E-Qlw&s"
                  }
                  alt="Processed Image"
                  className="w-full h-full object-cover"
                />
              </div>
              <div>
                    <h3>Analysis Results</h3>
                    <section className="mt-10 text-white">
                    <h3 className="text-2xl font-bold mb-4">Analysis Results</h3>
                        <p>Cars: {vehicleCount?.cars || 0}</p>
                        <p>Trucks: {vehicleCount?.trucks || 0}</p>
                        <p>Bikes: {vehicleCount?.bikes || 0}</p>
                        <p>Green Light Duration: {greenLightDuration || "N/A"} seconds</p>
                        <p>AQI: {aqi || "N/A"}</p>
                  </section>
                    
          </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
