// Import vue component
import launch from './launch';

if (typeof window !== 'undefined') {
    (window as any).powergrid = { launch };
}

export default launch;
