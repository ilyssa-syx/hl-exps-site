async function typedArray(url, Type) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Could not load ${url}: ${response.status}`);
  return new Type(await response.arrayBuffer());
}

export async function loadReconstruction(manifestUrl) {
  const response = await fetch(manifestUrl);
  if (!response.ok) throw new Error(`Could not load reconstruction: ${response.status}`);
  const metadata = await response.json();
  const root = new URL(".", response.url);
  const version = new URL(response.url).searchParams.get("v");
  const assetUrl = (relative) => {
    const url = new URL(relative, root);
    if (version) url.searchParams.set("v", version);
    return url;
  };
  const [handVertices, handFaces, objectVertices, objectFaces, objectPoses, objectUv] = await Promise.all([
    typedArray(assetUrl(metadata.hand.vertices), Float32Array),
    typedArray(assetUrl(metadata.hand.faces), Uint16Array),
    typedArray(assetUrl(metadata.object.vertices), Float32Array),
    typedArray(assetUrl(metadata.object.faces), Uint16Array),
    typedArray(assetUrl(metadata.object.poses), Float32Array),
    metadata.object.texture?.uv
      ? typedArray(assetUrl(metadata.object.texture.uv), Float32Array)
      : Promise.resolve(null),
  ]);
  const objectTextureUrl = metadata.object.texture?.image
    ? assetUrl(metadata.object.texture.image).toString()
    : null;
  return {
    metadata, handVertices, handFaces, objectVertices, objectFaces, objectPoses,
    objectUv, objectTextureUrl,
  };
}
