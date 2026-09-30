/** Pure npm publication decisions; network transport stays in the workflow. */
export function releaseChannel(version) {
  if (
    typeof version !== "string" ||
    !/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/.test(version)
  )
    throw new Error("semantic version is required");
  return version.split("+")[0].includes("-") ? "next" : "latest";
}

export function publicationDecision(remoteIntegrity, localIntegrity) {
  if (typeof localIntegrity !== "string" || !localIntegrity.startsWith("sha512-")) {
    throw new Error("local archive integrity is required");
  }
  if (remoteIntegrity === "") return { publish: true, reason: "absent" };
  if (typeof remoteIntegrity !== "string" || !remoteIntegrity.startsWith("sha512-")) {
    throw new Error("registry returned an invalid integrity");
  }
  if (remoteIntegrity !== localIntegrity) throw new Error("published version integrity differs");
  return { publish: false, reason: "identical" };
}
