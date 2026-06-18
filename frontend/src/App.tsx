import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Shell } from "./components/Shell";
import { Library } from "./pages/Library";
import { Analysis } from "./pages/Analysis";
import { Document } from "./pages/Document";
import { Memo } from "./pages/Memo";
import { Benchmark } from "./pages/Benchmark";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<Library />} />
          <Route path="/contracts/:id" element={<Analysis />} />
          <Route path="/contracts/:id/document" element={<Document />} />
          <Route path="/contracts/:id/memo" element={<Memo />} />
          <Route path="/benchmark" element={<Benchmark />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
