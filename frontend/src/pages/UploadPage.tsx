import { UploadForm } from "../components/UploadForm";

export function UploadPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Upload lecture material</h1>
        <p className="mt-1 text-sm text-ink-soft">
          We store the file name, upload date, course, lecture title and the extracted text, then
          run the analysis pipeline to build your study map.
        </p>
      </div>
      <UploadForm />
    </div>
  );
}
