import React, { useState } from 'react';
import '../login.css';
import { loginUser, Register } from '../api/user';
import { useNavigate } from 'react-router-dom';

interface Props {
  onLoginSuccess: (token: string) => void;
}

const LoginPage: React.FC<Props> = ({ onLoginSuccess }) => {
  const [isSignup, setIsSignup] = useState(false); // 회원가입 모드
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState(''); // 추가
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleLogin = async () => {
    try {
      const data = await loginUser(username, password);
      localStorage.setItem('access_token', data.access_token);
      onLoginSuccess(data.access_token);
      navigate('/interview');
    } catch (error) {
      alert('로그인 실패');
    }
  };

  const handleSignup = async () => {
    try {
      await Register(username, password, email); // email 포함
      alert('회원가입 성공! 로그인해주세요.');
      setIsSignup(false); // 로그인 화면으로 돌아감
    } catch (err) {
      alert('회원가입 실패: ' + err);
    }
  };

  return (
    
    <div className="login-container">
    <h2 className="login-title">Self Interview <span style={{ fontWeight: 300 }}>(S.I) : 셀프 면접</span></h2>
  
      <div className="login-box">
        <h2 className="login-title">{isSignup ? '🆕 회원가입' : '🔐 로그인'}</h2>

        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="아이디"
          className="login-input"
        />

        {isSignup && (
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="이메일"
            className="login-input"
          />
        )}

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="비밀번호"
          className="login-input"
        />

        {isSignup ? (
          <>
            <button onClick={handleSignup} className="signup-button">회원가입</button>
            <p style={{ marginTop: '1rem' }}>
              이미 계정이 있나요? <span onClick={() => setIsSignup(false)} style={{ color: 'blue', cursor: 'pointer' }}>로그인</span>
            </p>
          </>
        ) : (
          <>
            <button onClick={handleLogin} className="login-button">로그인</button>
            <p style={{ marginTop: '1rem' }}>
              계정이 없으신가요? <span onClick={() => setIsSignup(true)} style={{ color: 'blue', cursor: 'pointer' }}>회원가입</span>
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default LoginPage;
