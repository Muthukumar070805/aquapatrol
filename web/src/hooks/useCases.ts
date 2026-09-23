import { useQuery } from "@tanstack/react-query";
import { getCase, getCases, getReport } from "../lib/api";

export function useCases() {
  return useQuery({
    queryKey: ["cases"],
    queryFn: getCases,
  });
}

export function useCase(id: string | undefined) {
  return useQuery({
    queryKey: ["cases", id],
    queryFn: () => getCase(id ?? ""),
    enabled: id !== undefined && id !== "",
  });
}

export function useReport(caseId: string | undefined) {
  return useQuery({
    queryKey: ["reports", caseId],
    queryFn: () => getReport(caseId ?? ""),
    enabled: caseId !== undefined && caseId !== "",
  });
}
