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
  const [handVertices, handFaces, objectVertices, objectFaces, objectPoses] = await Promise.all([
    typedArray(new URL(metadata.hand.vertices, root), Float32Array),
    typedArray(new URL(metadata.hand.faces, root), Uint16Array),
    typedArray(new URL(metadata.object.vertices, root), Float32Array),
    typedArray(new URL(metadata.object.faces, root), Uint16Array),
    typedArray(new URL(metadata.object.poses, root), Float32Array),
  ]);
  return { metadata, handVertices, handFaces, objectVertices, objectFaces, objectPoses };
}
