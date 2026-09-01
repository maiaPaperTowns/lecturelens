import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";

import { Layout } from "./components/Layout";
import "./index.css";
import { ClusterViewPage } from "./pages/ClusterViewPage";
import { ConceptDetailPage } from "./pages/ConceptDetailPage";
import { LandingPage } from "./pages/LandingPage";
import { LectureDashboardPage } from "./pages/LectureDashboardPage";
import { ModelMetricsPage } from "./pages/ModelMetricsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PreviousLecturesPage } from "./pages/PreviousLecturesPage";
import { UploadPage } from "./pages/UploadPage";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "") || "/";

const router = createBrowserRouter(
  [
  {
    element: <Layout />,
    children: [
      { path: "/", element: <LandingPage /> },
      { path: "/upload", element: <UploadPage /> },
      { path: "/lectures", element: <PreviousLecturesPage /> },
      { path: "/lectures/:lectureId", element: <LectureDashboardPage /> },
      { path: "/lectures/:lectureId/clusters", element: <ClusterViewPage /> },
      { path: "/concepts/:conceptId", element: <ConceptDetailPage /> },
      { path: "/metrics", element: <ModelMetricsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  ],
  { basename },
);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
