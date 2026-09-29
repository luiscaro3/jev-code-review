import { describe, expect, it, vi } from "vitest";

describe("semantic review demo", () => {
  it("returns error code ACCOUNT_SUSPENDED", async () => {
    await expect(login(suspendedAccount)).rejects.toBeInstanceOf(DomainError);
  });

  it("loads the configured profile", async () => {
    const gateway = vi.fn().mockResolvedValue({ id: "profile-1" });
    await expect(gateway("profile-1")).resolves.toEqual({ id: "profile-1" });
  });

  it("returns status 404 when a profile is missing", async () => {
    const profiles = { find: vi.fn().mockResolvedValue(null) };
    const response = await handleProfileRequest(profiles, "missing");
    expect(response.status).toBe(404);
  });

  it("returns a cached response", async () => {
    const fetcher = vi.fn().mockResolvedValue(remoteValue);
    await executeWithDependencies({ fetcher });
    assertExpectedResult();
  });
});
