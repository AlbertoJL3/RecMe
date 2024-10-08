import React, { useState, useEffect, useRef, useCallback } from 'react';
import { submitPrompt, getPopularMovies, getWatchlist, addToWatchlist, removeFromWatchlist, refreshToken, savePromptResults, getPromptResults } from '../utils/api';
import { useAuth } from '../utils/AuthContext';
import Loading from '../components/Loading';
import MovieCard from '../components/MovieCard';
import '@fortawesome/fontawesome-free/css/all.min.css';
import '../styles/Home.css';

function Home() {
  const [popularMovies, setPopularMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [popularMoviesLoading, setPopularMoviesLoading] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [error, setError] = useState(null);
  const [promptResults, setPromptResults] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [watchlist, setWatchlist] = useState([]);
  const promptScrollContainerRef = useRef(null);
  const popularMoviesScrollContainerRef = useRef(null);
  const loadingRef = useRef(false);
  const { user, logout } = useAuth();

  const loadPopularMovies = useCallback(async (pageNum) => {
    if (loadingRef.current || !hasMore) return;
    loadingRef.current = true;
    setPopularMoviesLoading(true);
    try {
      const data = await getPopularMovies(pageNum);
      if (data.length === 0) {
        setHasMore(false);
      } else {
        setPopularMovies(prevMovies => {
          const newMovies = [...prevMovies, ...data];
          return newMovies.filter((movie, index, self) =>
            index === self.findIndex((t) => t.id === movie.id)
          );
        });
        setPage(pageNum);
      }
    } catch (err) {
      console.error('Failed to fetch popular movies:', err);
      if (err.response && err.response.status === 401) {
        try {
          await refreshToken();
          // Retry loading popular movies after refreshing token
          await loadPopularMovies(pageNum);
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          logout();  // Force logout if token refresh fails
        }
      }
      setHasMore(false);
    } finally {
      setPopularMoviesLoading(false);
      loadingRef.current = false;
    }
  }, [hasMore, logout]);

  useEffect(() => {
    if (user) {
      loadPopularMovies(1);
      loadWatchlist();      
    }
  }, [user, loadPopularMovies]);

  const loadWatchlist = async () => {
    try {
      const watchlistData = await getWatchlist();
      setWatchlist(watchlistData);
    } catch (err) {
      console.error('Failed to load watchlist:', err);
    }
  };

  const handleWatchlistChange = async (movieId, isAdding) => {
    try {
      if (isAdding) {
        await addToWatchlist(movieId);
        setWatchlist(prev => [...prev, { _id: movieId }]);
      } else {
        await removeFromWatchlist(movieId);
        setWatchlist(prev => prev.filter(m => m._id !== movieId));
      }
    } catch (err) {
      console.error('Failed to update watchlist:', err);
    }
  };

  const handlePromptSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const results = await submitPrompt(prompt);
      setPromptResults(results);
      // Save prompt results
      setPrompt('');
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

  const scroll = useCallback((direction, containerRef) => {
    const container = containerRef.current;
    if (container) {
      const scrollAmount = container.offsetWidth * 0.8;
      container.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      });
    }
  }, []);

  const handleRightScroll = useCallback(() => {
    const container = popularMoviesScrollContainerRef.current;
    if (container) {
      const scrollAmount = container.offsetWidth * 0.8;
      const maxScroll = container.scrollWidth - container.clientWidth;
      
      container.scrollBy({
        left: scrollAmount,
        behavior: 'smooth'
      });

      if (container.scrollLeft + scrollAmount >= maxScroll * 0.8 && 
          !loadingRef.current && 
          hasMore) {
        loadPopularMovies(page + 1);
      }
    }
  }, [loadPopularMovies, page, hasMore]);
  
  if (loading) {
    return <Loading />;
  }

  return (
    <div className="movies-page">
      <h3>Not sure what to watch? Ask our AI.</h3>
      <form className="prompt-form" onSubmit={handlePromptSubmit}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What's your movie mood?"
        />
        <button type="submit" aria-label="Submit" className="submit-button">
          <i className="fas fa-check"></i>
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {promptResults.length > 0 && (
        <div className="prompt-results-wrapper">
          <h2>Prompt Results</h2>
          <div className="scroll-container">
            <button className="scroll-button left" onClick={() => scroll('left', promptScrollContainerRef)} aria-label="Scroll left">
              <i className="fas fa-chevron-left"></i>
            </button>
            <div className="prompt-results-container" ref={promptScrollContainerRef}>
              {promptResults.map((movie) => (
                <div className="movie-card-wrapper" key={movie.id}>
                  <MovieCard 
                    movie={movie} 
                    isInWatchlist={watchlist.some(w => w._id === movie._id)}
                    onWatchlistChange={handleWatchlistChange}
                  />
                </div>
              ))}
            </div>
            <button className="scroll-button right" onClick={() => scroll('right', promptScrollContainerRef)} aria-label="Scroll right">
              <i className="fas fa-chevron-right"></i>
            </button>
          </div>
        </div>
      )}

      <h1>Popular Movies</h1>
      <div className="prompt-results-wrapper">
        <div className="scroll-container">
          <button 
            className="scroll-button left" 
            onClick={() => scroll('left', popularMoviesScrollContainerRef)} 
            aria-label="Scroll left"
          >
            <i className="fas fa-chevron-left"></i>
          </button>
          <div className="prompt-results-container" ref={popularMoviesScrollContainerRef}>
            {popularMovies.map((movie) => (
              <div className="movie-card-wrapper" key={movie.id}>
                <MovieCard 
                  movie={movie} 
                  isInWatchlist={watchlist.some(w => w._id === movie._id)}
                  onWatchlistChange={handleWatchlistChange}
                />
              </div>
            ))}
            {popularMoviesLoading && (
              <div className="loading-animation">
                <div className="spinner"></div>
              </div>
            )}
          </div>
          {hasMore && (
            <button 
              className="scroll-button right" 
              onClick={handleRightScroll}
              disabled={popularMoviesLoading}
              aria-label="Scroll right"
            >
              <i className="fas fa-chevron-right"></i>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default Home;