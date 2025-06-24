import React, { useEffect } from 'react';
import Clarity from '@microsoft/clarity';

const ClarityAnalytics = () => {
  useEffect(() => {
    const projectId = "rizkoien5v";
    Clarity.init(projectId);
  }, []);

  return null;
};

export default ClarityAnalytics; 