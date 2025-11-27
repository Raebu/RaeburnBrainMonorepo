import jwt from "jsonwebtoken";

export default function auth(req, res, next) {
  const token = req.headers.authorization;

  if (!token) {
    return res.status(401).json({ message: "Missing token" });
  }

  try {
    const decoded = jwt.verify(token.replace("Bearer ", ""), process.env.AUTH_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ message: "Invalid token" });
  }
}
