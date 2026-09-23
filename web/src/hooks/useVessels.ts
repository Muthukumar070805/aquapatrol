import { useQuery } from "@tanstack/react-query";
import { getVessels, getVesselTrack } from "../lib/api";

export function useVessels() {
  return useQuery({
    queryKey: ["vessels"],
    queryFn: getVessels,
  });
}

export function useVesselTrack(vesselId: string | null) {
  return useQuery({
    queryKey: ["vessels", vesselId, "track"],
    queryFn: () => getVesselTrack(vesselId ?? ""),
    enabled: vesselId !== null && vesselId !== "",
  });
}
