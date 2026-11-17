// Route handlers: a malformed POST body is the client's fault (400), never a server error (500).
export async function readForm(request: Request): Promise<FormData | null> {
  try {
    return await request.formData();
  } catch {
    return null;
  }
}
