import numpy as np 

from utils import MemoryDataSet, _mk_random
from libertem import api
from libertem.udf.pca import run_pca

def eig_error(eig_approx, eig):
    """
    Compute the correlation between the approximated eigenvalues
    and the true eigenvalues (computed using PCA on full-batch data)
    through inner product.

    Parameters
    ----------
    eig_approx: numpy.array
        Approximation of eigenvalues

    eig: numpy.array
        True eigenvalues as computed by PCA on full-batch data
    """
    corr = np.linalg.norm(eig_approx-eig)
    corr = np.inner(eig_approx, eig)
    return corr


def subspace_error(U_approx, U):
    """
    Compute the frobenius distance between the approximated left
    singular matrix and the exact left singular matrix (computed
    using PCA on full-batch data)

    Parameters
    -----------
    U_approx: numpy.array
        Approximation of eigenspace matrix

    U: numpy.array
        True eigenspace matrix as computed by PCA on full-batch data

    Returns
    -------
    err: float32
        Approximation error defined by the frobenius distance norm
        between the approximation and the true error
    """
    n_components = U.shape[1]
    A = U_approx.dot(U)
    B = U_approx.T.dot(U_approx)

    err = np.sqrt(n_components+np.trace(B.dot(B)) - 2 * np.trace(A.dot(A.T)))

    frob = np.linalg.norm(U-U_approx.T, ord='fro')

    return err/np.sqrt(n_components )

def mult(A, B):
    """
    default matrix multiplication.
    Multiplies A and B together via the "dot" method.
    Parameters
    ----------
    A : array_like
        first matrix in the product A*B being calculated
    B : array_like
        second matrix in the product A*B being calculated
    Returns
    -------
    array_like
        product of the inputs A and B
    Examples
    --------
    >>> from fbpca import mult
    >>> from numpy import array
    >>> from numpy.linalg import norm
    >>>
    >>> A = array([[1., 2.], [3., 4.]])
    >>> B = array([[5., 6.], [7., 8.]])
    >>> norm(mult(A, B) - A.dot(B))
    This example multiplies two matrices two ways -- once with mult,
    and once with the usual "dot" method -- and then calculates the
    (Frobenius) norm of the difference (which should be near 0).
    """

    if issparse(B) and not issparse(A):
        # dense.dot(sparse) is not available in scipy.
        return B.T.dot(A.T).T
    else:
        return A.dot(B)

def eig_error(eig_approx, eig):
	"""
	Compute the correlation between the approximated eigenvalues
	and the true eigenvalues (computed using PCA on full-batch data)
	through inner product.

	Parameters
	----------
	eig_approx: numpy.array
		Approximation of eigenvalues

	eig: numpy.array
		True eigenvalues as computed by PCA on full-batch data
	"""
	corr = np.linalg.norm(eig_approx-eig)
	corr = np.inner(eig_approx, eig)
	return corr

def diffsnorm(A, U, s, Va, n_iter=20):
    """
    2-norm accuracy of an approx to a matrix.
    Computes an estimate snorm of the spectral norm (the operator norm
    induced by the Euclidean vector norm) of A - U diag(s) Va, using
    n_iter iterations of the power method started with a random vector;
    n_iter must be a positive integer.
    Increasing n_iter improves the accuracy of the estimate snorm of
    the spectral norm of A - U diag(s) Va.
    Notes
    -----
    To obtain repeatable results, reset the seed for the pseudorandom
    number generator.
    Parameters
    ----------
    A : array_like
        first matrix in A - U diag(s) Va whose spectral norm is being
        estimated
    U : array_like
        second matrix in A - U diag(s) Va whose spectral norm is being
        estimated
    s : array_like
        vector in A - U diag(s) Va whose spectral norm is being
        estimated
    Va : array_like
        fourth matrix in A - U diag(s) Va whose spectral norm is being
        estimated
    n_iter : int, optional
        number of iterations of the power method to conduct;
        n_iter must be a positive integer, and defaults to 20
    Returns
    -------
    float
        an estimate of the spectral norm of A - U diag(s) Va (the
        estimate fails to be accurate with exponentially low prob. as
        n_iter increases; see references DM1_, DM2_, and DM3_ below)
    Examples
    --------
    >>> from fbpca import diffsnorm, pca
    >>> from numpy.random import uniform
    >>> from scipy.linalg import svd
    >>>
    >>> A = uniform(low=-1.0, high=1.0, size=(100, 2))
    >>> A = A.dot(uniform(low=-1.0, high=1.0, size=(2, 100)))
    >>> (U, s, Va) = svd(A, full_matrices=False)
    >>> A = A / s[0]
    >>>
    >>> (U, s, Va) = pca(A, 2, True)
    >>> err = diffsnorm(A, U, s, Va)
    >>> print(err)
    This example produces a rank-2 approximation U diag(s) Va to A such
    that the columns of U are orthonormal, as are the rows of Va, and
    the entries of s are all nonnegative and are nonincreasing.
    diffsnorm(A, U, s, Va) outputs an estimate of the spectral norm of
    A - U diag(s) Va, which should be close to the machine precision.
    References
    ----------
    .. [DM1] Jacek Kuczynski and Henryk Wozniakowski, Estimating the
             largest eigenvalues by the power and Lanczos methods with
             a random start, SIAM Journal on Matrix Analysis and
             Applications, 13 (4): 1094-1122, 1992.
    .. [DM2] Edo Liberty, Franco Woolfe, Per-Gunnar Martinsson,
             Vladimir Rokhlin, and Mark Tygert, Randomized algorithms
             for the low-rank approximation of matrices, Proceedings of
             the National Academy of Sciences (USA), 104 (51):
             20167-20172, 2007. (See the appendix.)
    .. [DM3] Franco Woolfe, Edo Liberty, Vladimir Rokhlin, and Mark
             Tygert, A fast randomized algorithm for the approximation
             of matrices, Applied and Computational Harmonic Analysis,
             25 (3): 335-366, 2008. (See Section 3.4.)
    See also
    --------
    diffsnormc, pca
    """

    (m, n) = A.shape
    (m2, k) = U.shape
    k2 = len(s)
    l = len(s)
    (l2, n2) = Va.shape

    assert m == m2
    assert k == k2
    assert l == l2
    assert n == n2

    assert n_iter >= 1

    if np.isrealobj(A) and np.isrealobj(U) and np.isrealobj(s) and \
            np.isrealobj(Va):
        isreal = True
    else:
        isreal = False

    # Promote the types of integer data to float data.
    dtype = (A * 1.0).dtype

    if m >= n:

        #
        # Generate a random vector x.
        #
        if isreal:
            x = np.random.normal(size=(n, 1)).astype(dtype)
        else:
            x = np.random.normal(size=(n, 1)).astype(dtype) \
                + 1j * np.random.normal(size=(n, 1)).astype(dtype)

        x = x / norm(x)

        #
        # Run n_iter iterations of the power method.
        #
        for it in range(n_iter):
            #
            # Set y = (A - U diag(s) Va)x.
            #
            y = mult(A, x) - U.dot(np.diag(s).dot(Va.dot(x)))
            #
            # Set x = (A' - Va' diag(s)' U')y.
            #
            x = mult(y.conj().T, A).conj().T \
                - Va.conj().T.dot(np.diag(s).conj().T.dot(U.conj().T.dot(y)))

            #
            # Normalize x, memorizing its Euclidean norm.
            #
            snorm = norm(x)
            if snorm == 0:
                return 0
            x = x / snorm

        snorm = math.sqrt(snorm)

    if m < n:

        #
        # Generate a random vector y.
        #
        if isreal:
            y = np.random.normal(size=(m, 1)).astype(dtype)
        else:
            y = np.random.normal(size=(m, 1)).astype(dtype) \
                + 1j * np.random.normal(size=(m, 1)).astype(dtype)

        y = y / norm(y)

        #
        # Run n_iter iterations of the power method.
        #
        for it in range(n_iter):
            #
            # Set x = (A' - Va' diag(s)' U')y.
            #
            x = mult(y.conj().T, A).conj().T \
                - Va.conj().T.dot(np.diag(s).conj().T.dot(U.conj().T.dot(y)))
            #
            # Set y = (A - U diag(s) Va)x.
            #
            y = mult(A, x) - U.dot(np.diag(s).dot(Va.dot(x)))

            #
            # Normalize y, memorizing its Euclidean norm.
            #
            snorm = norm(y)
            if snorm == 0:
                return 0
            y = y / snorm

        snorm = math.sqrt(snorm)

    return snorm

def test_pca(lt_ctx):
	"""
	Test Principal Component Analysis

    Parameters
    ----------
    lt_ctx
        Context class for loading dataset and creating jobs on them
	"""
	data = _mk_random(size=(32, 32, 32, 32), dtype="float32")
	dataset = MemoryDataSet(data=data, tileshape=(1, 16, 16),
							num_partitions=2, sig_dims=2)
	# with api.Context() as ctx:
	# 	path = '/home/jae/Downloads/scan_11_x256_y256.raw'
	# 	dataset = ctx.load(
	# 	'empad',
	# 	path=path,
	# 	scan_size=(256, 256),
	# 	)

	res = run_pca(lt_ctx, dataset, n_components=10)

	assert 'components' in res
	assert 'left_singular' in res
	assert 'singular_vals' in res

	left_singular = res['left_singular'].data
	singular_vals = res['singular_vals'].data
	components = res['components'].data


	reconstruct_loading = left_singular @ np.diag(singular_vals)

	print("loading shape: ", reconstruct_loading.shape)
	print("Component shape: ", components.shape)
	reconstruct_data = reconstruct_loading @ components

	data = data.reshape((data.shape[0]*data.shape[1], data.shape[2]*data.shape[3]))
	# print("data shape: ", data.shape)
	# U, S, V = fbpca.pca(data, k=100)

	# loading = U @ np.diag(S)
	# orig_data = loading @ V
	# print("orig_data reconstructed: ", orig_data.shape)
	# print("reconstructed using pca: ", reconstruct_data.shape)
	raise ValueError(diffsnorm(data, left_singular, singular_vals, components))

	# N = data.shape[2] * data.shape[3]
	# assert res['num_frame'].data == N

	# flattened = data.reshape((1024, 1024))
	# U, D, V = np.linalg.svd(flattened)

	# # normalize the singular values for comparison
	# D = D / np.linalg.norm(D)
	# eig_approx = res['singular_vals'].data
	# eig_approx = eig_approx / np.linalg.norm(eig_approx)

	# tol = 1

	# assert eig_error(eig_approx, D[:9]) < tol
	# assert subspace_error(res['left_singular'].data, U[:9]) < tol

	# TODO: Find the appropriate tolerance error bound