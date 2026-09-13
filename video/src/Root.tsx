import React from 'react';
import {Composition} from 'remotion';
import {Anderson, AndersonFeed, TOTAL} from './Anderson';

export const Root: React.FC = () => (
  <>
    {/* the film */}
    <Composition
      id="Anderson"
      component={Anderson}
      durationInFrames={TOTAL}
      fps={30}
      width={1920}
      height={1080}
    />
    {/* 4:5, the shape LinkedIn gives the most feed height to */}
    <Composition
      id="AndersonPortrait"
      component={AndersonFeed}
      durationInFrames={TOTAL}
      fps={30}
      width={1080}
      height={1350}
      defaultProps={{width: 1080, height: 1350}}
    />
    {/* 1:1 */}
    <Composition
      id="AndersonSquare"
      component={AndersonFeed}
      durationInFrames={TOTAL}
      fps={30}
      width={1080}
      height={1080}
      defaultProps={{width: 1080, height: 1080}}
    />
  </>
);
