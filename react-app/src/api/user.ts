// src/api/user.ts

export const loginUser = async (email: string, password: string) => {
  const response = await fetch("http://localhost:8000/api/user/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error("로그인 실패");
  }

  const data = await response.json(); // { access_token, token_type }
  
  // localStorage 또는 sessionStorage에 저장
  localStorage.setItem("token", data.access_token);

  return data;
};



export const  Register = async (username: string, password: string,email : string) => {
  const response = await fetch("http://localhost:8000/api/user/Register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password ,email}),
  });

  if (!response.ok) {
    throw new Error("회원가입 실패");
  }
  return true;
};
