import React from 'react';
import {Composition} from 'remotion';
import {Anderson, TOTAL} from './Anderson';

export const Root: React.FC = () => (
  <>
    <Composition
      id="Anderson"
      component={Anderson}
      durationInFrames={TOTAL}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
