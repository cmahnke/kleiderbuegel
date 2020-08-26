Mock for Kleiderbügel Blog
==========================

# Starting

```
yarn serve
```

Point your browser to [http://localhost:5000/kleiderschrank.html](http://localhost:5000/kleiderschrank.html)

# Documentation for the Cover Flow thing

 * [jquery-flipster](https://github.com/drien/jquery-flipster)


# Generating Images for the Kleiderstange

```
find . -name '*.png' -exec convert {} -resize 330x  {}.thmb.png \;
```
