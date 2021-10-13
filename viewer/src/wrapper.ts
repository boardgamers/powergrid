// Import vue component
import launch from './launch';

if (typeof window !== 'undefined') {
    (window as any).container = { launch };
}

export default launch;
