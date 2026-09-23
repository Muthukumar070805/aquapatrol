import { useMutation } from "@tanstack/react-query";
import { detectYoloImage } from "../lib/api";

interface YoloDetectVars {
  file: Blob;
  filename?: string;
}

export function useYoloDetect() {
  return useMutation({
    mutationFn: ({ file, filename }: YoloDetectVars) =>
      detectYoloImage(file, filename),
  });
}
