import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Library } from "./pages/Library";
import { Analysis } from "./pages/Analysis";
import { Summary } from "./pages/Summary";
import { BatchCompare } from "./pages/BatchCompare";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Library />} />
        <Route path="/contracts/:id" element={<Analysis />} />
        <Route path="/contracts/:id/summary" element={<Summary />} />
        <Route path="/compare" element={<BatchCompare />} />
      </Routes>
    </BrowserRouter>
  );
}
