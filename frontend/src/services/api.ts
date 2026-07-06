export async function apiGet(path){
  const res = await fetch(path)
  return res.json()
}
