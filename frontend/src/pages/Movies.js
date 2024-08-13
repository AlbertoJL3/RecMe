import React, { useState, useEffect, useRef } from 'react';
import { fetchMovies, submitPrompt } from '../utils/api';
import Loading from '../components/Loading';
import MovieCard from '../components/MovieCard';
import '@fortawesome/fontawesome-free/css/all.min.css';

function Movies() {
  const [movies, setMovies] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [promptResults, setPromptResults] = useState([]);
  const scrollContainerRef = useRef(null);
  

  useEffect(() => {
    loadMovies();
  }, []);

  const loadMovies = async () => {
    setLoading(true);
    try {
      const data = await fetchMovies();
      console.log("Fetched movies:", data);  // Add this line
      setMovies(data);
    } catch (err) {
      setError('Failed to load movies');
    } finally {
      setLoading(false);
    }
  };

  const setGlassColor = (color) => {
    document.documentElement.style.setProperty('--glass-color', color);
  };

  const handlePromptSubmit = async (e) => {
    e.preventDefault();
    if(!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const results = await submitPrompt(prompt);
      console.log("Prompt results:", results);  // Add this line
      setPromptResults(results);
      setPrompt('');
      setGlassColor('rgba(255, 255, 255, 0.1)');
      setTimeout(() => {
        const resultsWrapper = document.querySelector('.prompt-results-wrapper');
        if (resultsWrapper) {
          resultsWrapper.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
    } catch (err) {
      setError('Failed to process prompt');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handlePromptSubmit(e);
    }
  };

  const scroll = (direction) => {
    const container = scrollContainerRef.current;
    if (container) {
      const scrollAmount = container.offsetWidth * 0.8; // Scroll 80% of the container width
      container.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      });
    }
  };

  if (loading) {
    return <Loading />;
  }

  return (
    <div className="movies-page">
      <h2>All Movies</h2>
      <div className="movie-list">
        {movies.map(movie => (
          <MovieCard key={movie.id} movie={movie} />
        ))}
      </div>
      {error && <div className="error">{error}</div>}
    </div>
  );
}

export default Movies;